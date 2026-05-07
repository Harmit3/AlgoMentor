import os
from groq import Groq
import chromadb
from sentence_transformers import SentenceTransformer
from prompts import build_prompt
import re
from typing import Optional


def strip_code(reply: str) -> str:
    reply = re.sub(r"```.*?```", "[code removed]", reply, flags=re.DOTALL)
    return reply.strip()


MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

STUCK_PHRASES = ["i don't know", "no idea", "i'm stuck", "im stuck", "not sure", "idk", "help"]
GIVE_UP_PHRASES = ["just tell me", "give up", "what's the answer", "tell me the answer"]
ANSWER_SEEKING_PHRASES = GIVE_UP_PHRASES + ["show me the code", "write the code", "solve it for me"]
VALIDATION_PHRASES = ["is this right", "does this make sense", "am i on the right track", "is my approach correct", "would this work"]
DEBUG_PHRASES = ["fails on", "wrong answer", "times out", "timeout", "bug", "edge case", "doesn't work", "not working"]
CONFIRMATION_CUES = ["yes", "right", "correct", "exactly", "got it", "that makes sense"]
HYPOTHESIS_CUES = ["i think", "maybe", "what if", "could i", "my idea", "my approach", "should i", "can i", "can we", "what about"]

DIRECT_SOLUTION_PATTERNS = [
    r"\bhash\s*map\b",
    r"\bhashmap\b",
    r"\bdictionary\b",
    r"\btwo pointers?\b",
    r"\bsliding window\b",
    r"\bbinary search\b",
    r"\bdepth[- ]first search\b",
    r"\bbreadth[- ]first search\b",
    r"\bdfs\b",
    r"\bbfs\b",
    r"\bdijkstra\b",
    r"\bbellman[- ]ford\b",
    r"\bunion[- ]find\b",
    r"\bdisjoint set\b",
    r"\bpriority queue\b",
    r"\bheap\b",
]

CODE_PATTERNS = [
    r"```",
    r"\bdef\b",
    r"\bclass\b",
    r"\breturn\b",
    r"{",
    r"}",
    r";",
]

FOCUS_SORTING = "sorting_indices"
FOCUS_COMPLEMENT = "complement_value"
FOCUS_LOOKUP = "fast_lookup"
FOCUS_STORED_INFO = "stored_info"
FOCUS_KEY_VALUE = "key_value_mapping"

embedder = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./chroma_db")


def get_or_create_collection():
    return chroma_client.get_or_create_collection("algo_corpus")


def classify_intent(message: str) -> str:
    msg = message.lower()

    if any(p in msg for p in GIVE_UP_PHRASES):
        return "give_up"
    if any(p in msg for p in STUCK_PHRASES):
        return "stuck"
    if any(p in msg for p in DEBUG_PHRASES):
        return "debug"
    if any(p in msg for p in VALIDATION_PHRASES):
        return "validate"

    return "normal"


def update_student_state(session: dict, student_message: str, intent: str) -> None:
    msg = student_message.strip()
    lower_msg = msg.lower()

    is_hypothesis = any(cue in lower_msg for cue in HYPOTHESIS_CUES)

    mentions_candidate_strategy = any(
        term in lower_msg
        for term in ["sort", "sorted", "reorder", "brute force", "nested loop", "two loops"]
    )

    if intent in ("validate", "debug"):
        session["tutor_mode"] = "reasoning_check"
    elif intent == "stuck":
        session["tutor_mode"] = "guided_hint"
    elif intent == "give_up":
        session["tutor_mode"] = "boundary_refusal"
    elif is_hypothesis and mentions_candidate_strategy:
        session["tutor_mode"] = "reasoning_check"
    elif is_hypothesis:
        session["tutor_mode"] = "strategy_coaching"
    else:
        session["tutor_mode"] = "guided_hint"

    if is_hypothesis or intent in ("validate", "debug"):
        session["student_hypotheses"].append(msg)

    if any(cue in lower_msg for cue in CONFIRMATION_CUES):
        session["confirmed_knowledge"].append(msg)
        return

    if intent == "normal":
        word_count = len(msg.split())
        if 1 <= word_count <= 4 and "?" not in msg:
            session["confirmed_knowledge"].append(msg)


def set_focus_from_reply(session: dict, reply: str) -> None:
    lower_reply = reply.lower()

    if "original positions" in lower_reply or "original indices" in lower_reply:
        session["current_focus"] = FOCUS_SORTING
    elif "partner value" in lower_reply or "complete the target" in lower_reply:
        session["current_focus"] = FOCUS_COMPLEMENT
    elif "checking for a needed value fast" in lower_reply or "seen it quickly" in lower_reply:
        session["current_focus"] = FOCUS_LOOKUP
    elif "key and value" in lower_reply or "key be" in lower_reply or "value represent" in lower_reply:
        session["current_focus"] = FOCUS_KEY_VALUE
    elif "what information might be worth remembering" in lower_reply or "stored information" in lower_reply:
        session["current_focus"] = FOCUS_STORED_INFO


def maybe_rule_based_reply(session: dict, student_message: str, intent: str) -> Optional[str]:
    lower_msg = student_message.strip().lower()
    focus = session["current_focus"]

    if "sort" in lower_msg:
        session["current_focus"] = FOCUS_SORTING
        return "No, sorting changes the order, which makes the original indices harder to recover. What kind of lookup would let you avoid reordering the array?"

    if focus == FOCUS_SORTING and any(phrase in lower_msg for phrase in ["or no", "is that bad", "would that work", "shall we"]):
        return "No, because sorting changes positions. What lookup could help you find the needed value without changing the array?"

    if "hashmap" in lower_msg or "hash map" in lower_msg or "dictionary" in lower_msg:
        session["current_focus"] = FOCUS_LOOKUP

        if "two hashmap" in lower_msg or "two hashmaps" in lower_msg or "two dictionaries" in lower_msg:
            return "You only need one, because each seen number can map to its index. If you use one map, what should its key and value represent?"

        if "one hashmap" in lower_msg or "one hash map" in lower_msg:
            return "Yes, one map is enough because lookup and index recovery can live together. What should the key and value represent?"

        if "is that correct" in lower_msg or "is that right" in lower_msg or "correct?" in lower_msg:
            return "Yes, that direction makes sense because it gives fast lookup without reordering. If you use one map, what should its key and value represent?"

        return "Yes, that direction makes sense because it gives fast lookup. What should the key and value represent?"

    if any(token in lower_msg for token in ["target-x", "target - x", "target minus x", "complement"]):
        session["current_focus"] = FOCUS_COMPLEMENT

        if "?" in lower_msg or intent == "validate":
            return "Yes, that is the partner value. How could you tell quickly whether you have already seen it?"

        return "Yes, that is the partner value. How could you check whether you have already seen it quickly?"

    if focus == FOCUS_COMPLEMENT and ("is that right" in lower_msg or lower_msg in {"right?", "correct?", "yes?"}):
        return "Yes, that is the partner value. How could you tell quickly whether you have already seen it?"

    if focus == FOCUS_COMPLEMENT and lower_msg in {"target - x", "target-x", "complement"}:
        return "Yes, that is the partner value. How could you check whether you have already seen it quickly?"

    if focus == FOCUS_LOOKUP and any(phrase in lower_msg for phrase in ["is that right", "what then", "then what", "okay"]):
        return "Yes, fast lookup is the goal because repeated searching would be slow. What earlier information would you need to remember?"

    if focus == FOCUS_STORED_INFO and any(token in lower_msg for token in ["index", "position"]):
        session["current_focus"] = FOCUS_KEY_VALUE
        return "Yes, the position matters because you need to return indices. If that is the value, what should the key be so lookup stays fast?"

    if "key" in lower_msg and "value" in lower_msg and any(token in lower_msg for token in ["number", "index", "indices"]):
        session["current_focus"] = FOCUS_KEY_VALUE
        return "Yes, that is the right mapping because the number supports lookup and the index gives the answer position. When would you check for the partner value: before or after storing the current number?"

    if focus == FOCUS_KEY_VALUE and any(token in lower_msg for token in ["number", "index", "indices"]):
        return "Yes, that mapping works because it lets you find a seen number and recover its position. When should you check for the partner value: before or after storing the current number?"

    if intent == "stuck":
        if focus == FOCUS_KEY_VALUE:
            return "You want one map where the key is the number and the value is its index. Once you have that, when should you look for the partner value?"

        if focus == FOCUS_LOOKUP:
            return "You want a structure that lets you check whether a number was seen before very quickly. If you use one map, what should it store?"

        if focus == FOCUS_COMPLEMENT:
            return "You are looking for target minus x. What stored information would let you test whether that value appeared earlier?"

    return None


def sanitize_chunk(text: str) -> str:
    sanitized = text

    sanitized = re.sub(
        r"CORRECT APPROACH:.*?(?:\.|$)",
        "CORRECT APPROACH: [hidden for tutoring]. ",
        sanitized,
        flags=re.IGNORECASE,
    )

    sanitized = re.sub(
        r"WRONG APPROACHES:.*?(?:\.|$)",
        "WRONG APPROACHES: [hidden for tutoring]. ",
        sanitized,
        flags=re.IGNORECASE,
    )

    sanitized = re.sub(
        r"Use [A-Z][A-Za-z-]*(?: [A-Z][A-Za-z-]*)* instead",
        "Use a more suitable method instead",
        sanitized,
    )

    sanitized = re.sub(r"\bhash\s*map\b", "[hidden structure]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"\bhashmap\b", "[hidden structure]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"\bdictionary\b", "[hidden structure]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"\bpriority queue\b", "[hidden structure]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"\bBellman-Ford\b", "[hidden algorithm]", sanitized, flags=re.IGNORECASE)

    return sanitized.strip()


def retrieve_chunks(query: str, n=3) -> list[str]:
    collection = get_or_create_collection()

    if collection.count() == 0:
        return []

    results = collection.query(query_texts=[query], n_results=min(n, collection.count()))

    return [sanitize_chunk(doc) for doc in results["documents"][0]]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def is_repeated_question(reply: str, session: dict) -> bool:
    reply_norm = normalize(reply)
    return any(normalize(prev) == reply_norm for prev in session["hints_given"])


def looks_like_code(reply: str) -> bool:
    return any(re.search(pattern, reply, flags=re.IGNORECASE) for pattern in CODE_PATTERNS)


def reveals_direct_solution(reply: str, student_message: str) -> bool:
    student_lower = student_message.lower()

    if any(phrase in student_lower for phrase in ANSWER_SEEKING_PHRASES):
        return False

    return any(re.search(pattern, reply, flags=re.IGNORECASE) for pattern in DIRECT_SOLUTION_PATTERNS)


def fallback_question(session: dict, student_message: str) -> str:
    confirmed_text = " ".join(session["confirmed_knowledge"]).lower()
    hypotheses_text = " ".join(session["student_hypotheses"]).lower()
    focus = session["current_focus"]

    if focus == FOCUS_COMPLEMENT:
        return "How could you check whether you have already seen that partner value quickly?"

    if focus == FOCUS_LOOKUP:
        return "What information would you want to store so that lookup stays fast?"

    if focus == FOCUS_KEY_VALUE:
        return "If you use one map, what should the key and value represent?"

    if focus == FOCUS_STORED_INFO:
        return "If you store that information, what should the key and value represent?"

    if session["tutor_mode"] == "reasoning_check":
        if any(term in hypotheses_text for term in ["sort", "sorted", "reorder"]):
            session["current_focus"] = FOCUS_SORTING
            return "If you reorder the input, how will you recover the original positions?"

        if any(term in hypotheses_text for term in ["nested loop", "two loops", "brute force"]):
            return "How would that approach scale if the input were much larger?"

        return "What assumption does your approach rely on, and can you test it on a tiny example?"

    if "key" in confirmed_text and "value" in confirmed_text:
        session["current_focus"] = FOCUS_STORED_INFO
        return "What would that stored information let you recover at the end?"

    if "key" in confirmed_text:
        session["current_focus"] = FOCUS_STORED_INFO
        return "If that is the key, what should the value represent?"

    if "store" in confirmed_text or "remember" in confirmed_text:
        session["current_focus"] = FOCUS_STORED_INFO
        return "What exact piece of information would help you produce the final answer?"

    stuck_count = session["stuck_count"]

    if stuck_count <= 0:
        return "What constraint or detail in the problem seems most useful?"

    if stuck_count == 1:
        session["current_focus"] = FOCUS_LOOKUP
        return "What would make checking for a needed value fast?"

    if stuck_count == 2:
        session["current_focus"] = FOCUS_STORED_INFO
        return "If you process the input once, what information might be worth remembering?"

    return "Try a tiny example by hand: what would you want to have seen earlier?"


def safe_reply(model_reply: str, session: dict, student_message: str) -> str:
    cleaned = strip_code(model_reply)

    if not cleaned:
        return fallback_question(session, student_message)

    if looks_like_code(cleaned):
        return fallback_question(session, student_message)

    if reveals_direct_solution(cleaned, student_message):
        return fallback_question(session, student_message)

    if is_repeated_question(cleaned, session):
        return fallback_question(session, student_message)

    sentences = re.split(r"(?<=[?!\.])\s+", cleaned)
    trimmed = " ".join(sentences[:2]).strip()

    if len(trimmed.split()) > 35:
        return fallback_question(session, student_message)

    return trimmed


def session_status(session: dict) -> str:
    mode_labels = {
        "guided_hint": "Guided hint mode",
        "strategy_coaching": "Strategy coaching mode",
        "reasoning_check": "Reasoning check mode",
        "boundary_refusal": "No-solution boundary mode",
    }

    label = mode_labels.get(session["tutor_mode"], "Guided hint mode")
    confirmed = len(session["confirmed_knowledge"])
    hypotheses = len(session["student_hypotheses"])

    return f"{label} | stuck level: {session['stuck_count']} | confirmed ideas: {confirmed} | active guesses: {hypotheses}"


def new_session(problem: str) -> dict:
    return {
        "problem": problem,
        "hints_given": [],
        "confirmed_knowledge": [],
        "student_hypotheses": [],
        "stuck_count": 0,
        "tutor_mode": "guided_hint",
        "current_focus": None,
        "messages": [],
    }


def call_groq_model(system_prompt: str, recent_messages: list[dict]) -> str:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return "The online model is not configured yet. Please add GROQ_API_KEY in the deployment secrets."

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system_prompt}] + recent_messages,
        temperature=0.3,
        max_completion_tokens=120,
    )

    return response.choices[0].message.content


def tutor_turn(session: dict, student_message: str) -> tuple[str, dict]:
    intent = classify_intent(student_message)

    if intent in ("give_up", "stuck"):
        session["stuck_count"] += 1

    update_student_state(session, student_message, intent)

    session["messages"].append({
        "role": "user",
        "content": student_message
    })

    forced_reply = maybe_rule_based_reply(session, student_message, intent)

    if forced_reply is not None:
        reply = forced_reply

        session["messages"].append({
            "role": "assistant",
            "content": reply
        })

        session["hints_given"].append(reply)
        set_focus_from_reply(session, reply)

        if intent == "normal" and len(student_message.split()) > 6:
            session["stuck_count"] = max(0, session["stuck_count"] - 1)

        return reply, session

    query = session["problem"] + " " + student_message
    chunks = retrieve_chunks(query)

    system = build_prompt(session, chunks)
    recent_messages = session["messages"][-10:]

    model_reply = call_groq_model(system, recent_messages)
    reply = safe_reply(model_reply, session, student_message)

    set_focus_from_reply(session, reply)

    session["messages"].append({
        "role": "assistant",
        "content": reply
    })

    session["hints_given"].append(reply)

    if intent == "normal" and len(student_message.split()) > 6:
        session["stuck_count"] = max(0, session["stuck_count"] - 1)

    return reply, session