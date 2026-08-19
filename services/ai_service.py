"""
ai_service.py
Talks to an AI provider (Groq or OpenAI, both OpenAI-compatible chat APIs)
to:
  1. detect_topics()  - find the main topics covered in a PDF's text
  2. generate_mcqs()  - generate multiple-choice questions strictly from
                         the supplied text, for a chosen topic/difficulty

Both functions ask the model to reply with JSON only, then parse and
validate that JSON defensively (models occasionally wrap output in
markdown fences or add stray text).
"""

import json
import os
import re
import requests

AI_PROVIDER = os.environ.get("AI_PROVIDER", "groq").lower()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class AIServiceError(Exception):
    """Raised when the AI provider is not configured or a call fails."""


def _provider_config():
    if AI_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise AIServiceError(
                "OPENAI_API_KEY is not set. Add it to your .env file, or set "
                "AI_PROVIDER=groq and provide GROQ_API_KEY instead."
            )
        return OPENAI_URL, OPENAI_API_KEY, OPENAI_MODEL
    else:
        if not GROQ_API_KEY:
            raise AIServiceError(
                "GROQ_API_KEY is not set. Get a free key at "
                "https://console.groq.com/keys and add it to your .env file."
            )
        return GROQ_URL, GROQ_API_KEY, GROQ_MODEL


def _call_ai(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
    """Send a chat completion request and return the raw text reply."""
    url, api_key, model = _provider_config()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": max_tokens,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
    except requests.RequestException as exc:
        raise AIServiceError(f"Could not reach the AI provider: {exc}") from exc

    if response.status_code != 200:
        raise AIServiceError(
            f"AI provider returned an error ({response.status_code}): {response.text[:300]}"
        )

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise AIServiceError("Unexpected response format from AI provider.") from exc


def _extract_json(raw_text: str):
    """Strip markdown fences / stray text and parse JSON from a model reply."""
    text = raw_text.strip()

    # Remove ```json ... ``` or ``` ... ``` fences if present.
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # If there's still leading/trailing junk, grab the first {...} or [...] block.
    if not (text.startswith("{") or text.startswith("[")):
        obj_match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if obj_match:
            text = obj_match.group(1)

    return json.loads(text)


def detect_topics(full_text: str) -> list:
    """
    Ask the AI to identify the main topics covered in the document.
    Returns a list of short topic-name strings (typically 4-8 topics).
    """
    excerpt = full_text[:15000]  # keep prompt size reasonable

    system_prompt = (
        "You are an assistant that analyzes study material for students. "
        "You read the given text extracted from a PDF and identify the main "
        "topics it covers. Reply with ONLY a valid JSON array of short topic "
        "name strings (4 to 8 topics), and nothing else. No markdown, no "
        "explanation, no preamble."
    )
    user_prompt = (
        "Identify the main topics covered in the following study material. "
        "Each topic name should be short (2-6 words) and specific to the "
        "content below.\n\n"
        f"STUDY MATERIAL:\n{excerpt}"
    )

    raw = _call_ai(system_prompt, user_prompt, max_tokens=500)

    try:
        topics = _extract_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise AIServiceError(f"Could not parse topics from AI response: {exc}") from exc

    if not isinstance(topics, list) or not topics:
        raise AIServiceError("AI did not return a valid list of topics.")

    # Clean up: keep only non-empty strings, dedupe, cap at 8.
    cleaned = []
    seen = set()
    for t in topics:
        if isinstance(t, str) and t.strip() and t.strip().lower() not in seen:
            cleaned.append(t.strip())
            seen.add(t.strip().lower())

    if not cleaned:
        raise AIServiceError("AI returned an empty topic list.")

    return cleaned[:8]


def generate_mcqs(text_excerpt: str, topic: str, num_questions: int, difficulty: str) -> list:
    """
    Generate `num_questions` multiple-choice questions about `topic`,
    using ONLY the supplied text_excerpt as source material.

    Returns a list of dicts:
        {
            "question": str,
            "options": [str, str, str, str],
            "correct_index": int (0-3),
            "explanation": str
        }
    """
    system_prompt = (
        "You are an exam question writer for students. You create multiple-choice "
        "questions using ONLY the study material provided to you. "
        "You NEVER invent facts that are not present in the material. "
        "Every question must have exactly 4 options with exactly one correct answer. "
        "Reply with ONLY a valid JSON array, no markdown, no explanation, no preamble."
    )

    user_prompt = f"""Using ONLY the study material below, write {num_questions} multiple-choice
questions about the topic "{topic}" at {difficulty} difficulty.

Rules:
- Base every question strictly on facts present in the study material. Do not add outside information.
- Each question must have exactly 4 options.
- Exactly one option must be correct.
- Vary the position of the correct answer across questions (don't always put it first).
- Keep questions clear and unambiguous.
- Provide a one-sentence explanation for why the correct answer is correct, referencing the material.

Reply with ONLY a JSON array in this exact shape:
[
  {{
    "question": "...",
    "options": ["...", "...", "...", "..."],
    "correct_index": 0,
    "explanation": "..."
  }}
]

STUDY MATERIAL:
{text_excerpt}
"""

    raw = _call_ai(system_prompt, user_prompt, max_tokens=4000)

    try:
        questions = _extract_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise AIServiceError(f"Could not parse questions from AI response: {exc}") from exc

    if not isinstance(questions, list) or not questions:
        raise AIServiceError("AI did not return a valid list of questions.")

    validated = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        question_text = q.get("question")
        options = q.get("options")
        correct_index = q.get("correct_index")
        explanation = q.get("explanation", "")

        if not isinstance(question_text, str) or not question_text.strip():
            continue
        if not isinstance(options, list) or len(options) != 4:
            continue
        if not all(isinstance(o, str) and o.strip() for o in options):
            continue
        if not isinstance(correct_index, int) or not (0 <= correct_index <= 3):
            continue

        validated.append(
            {
                "question": question_text.strip(),
                "options": [o.strip() for o in options],
                "correct_index": correct_index,
                "explanation": explanation.strip() if isinstance(explanation, str) else "",
            }
        )

    if not validated:
        raise AIServiceError("AI response did not contain any valid questions.")

    return validated[:num_questions]
