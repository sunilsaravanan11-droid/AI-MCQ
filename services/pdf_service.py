"""
pdf_service.py
Extracts clean text from an uploaded PDF using PyMuPDF (fitz).
"""

import fitz  # PyMuPDF


def extract_text_from_pdf(filepath: str) -> str:
    """Return the cleaned, concatenated text of every page in the PDF."""
    doc = fitz.open(filepath)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()

    full_text = "\n".join(pages)

    # Basic cleanup: drop empty/whitespace-only lines and excess blank lines.
    lines = [line.strip() for line in full_text.split("\n")]
    lines = [line for line in lines if line]
    cleaned = "\n".join(lines)

    return cleaned


def find_relevant_excerpt(full_text: str, topic: str, max_chars: int = 12000) -> str:
    """
    Pull the paragraphs most relevant to `topic` out of the full document text.
    This keeps MCQ generation focused on the selected topic and keeps the
    prompt sent to the AI within a reasonable size.

    Falls back to the first `max_chars` characters of the document if no
    paragraph scores well against the topic keywords.
    """
    if len(full_text) <= max_chars:
        return full_text

    # Split into paragraphs (blank-line separated, or fall back to sentence chunks).
    paragraphs = [p.strip() for p in full_text.split("\n") if p.strip()]

    keywords = [w.lower() for w in topic.split() if len(w) > 2]
    if not keywords:
        return full_text[:max_chars]

    scored = []
    for para in paragraphs:
        para_lower = para.lower()
        score = sum(para_lower.count(kw) for kw in keywords)
        if score > 0:
            scored.append((score, para))

    if not scored:
        return full_text[:max_chars]

    scored.sort(key=lambda x: x[0], reverse=True)

    excerpt_parts = []
    total_len = 0
    for score, para in scored:
        if total_len + len(para) > max_chars:
            continue
        excerpt_parts.append(para)
        total_len += len(para)
        if total_len >= max_chars:
            break

    excerpt = "\n".join(excerpt_parts)
    return excerpt if excerpt else full_text[:max_chars]
