import hashlib
import re
from datetime import datetime
from pathlib import Path

GENERATED_DIR = Path(__file__).resolve().parent / "generated"

def pre_filter_and_deduplicate(raw_html_or_text_list: list[str]) -> list[str]:
    """
    1) Deduplicates content strings using MD5 hashing.
    2) Extracts high-density semantic text snippets to minimize prompt payload.
    """
    seen_hashes = set()
    cleaned_results = []

    for raw_content in raw_html_or_text_list:
        if not raw_content:
            continue
            
        # 1. Simple Deduplication Check
        content_hash = hashlib.md5(raw_content.encode('utf-8')).hexdigest()
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)

        # 2. Context Pre-filtering & Light Cleaning
        # Strip script/style tags completely
        text = re.sub(r'<(script|style).*?>.*?</\1>', '', raw_content, flags=re.DOTALL | re.IGNORECASE)
        # Strip all other HTML tags
        text = re.sub(r'<[^>]*>', ' ', text)
        # Standardize whitespace characters
        text = re.sub(r'\s+', ' ', text).strip()

        # 3. Structural Semantic Extraction (Heuristics)
        # Keep sentences that possess high informational value (e.g. 5 to 45 words long)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        meaningful_snippets = []
        
        for sentence in sentences:
            words = sentence.split()
            if 5 <= len(words) <= 45:
                meaningful_snippets.append(sentence)
        
        # Reconstruct filtered content (Cap at ~1200 words per search response to secure high speed)
        filtered_text = " ".join(meaningful_snippets[:40]) 
        if filtered_text:
            cleaned_results.append(filtered_text)

    return cleaned_results

def is_simple_query(query: str) -> bool:
    """
    Intention Routing Matrix
    Checks if the request is straightforward enough to bypass multi-search agent tasks.
    """
    clean_query = query.strip().lower()

    # Regex patterns signaling rapid direct writing routes
    simple_patterns = [
        r"^what is\b",
        r"^what are\b",
        r"^define\b",
        r"^explain the concept of\b",
        r"^who is\b(?!.*deep history.*)",
        r"^how many\b"
    ]

    # Rule 1: Pattern Match
    if any(re.search(pattern, clean_query) for pattern in simple_patterns):
        return True

    # Rule 2: Token Length Fallback (Very short queries can be served faster directly)
    if len(clean_query.split()) <= 3:
        return True

    return False


def _slugify(query: str, max_len: int = 60) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", query.strip().lower()).strip("-")
    return slug[:max_len] or "report"


def _yaml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def save_report(query: str, markdown_report: str, trace_id: str) -> Path:
    """Persist the report as Markdown under generated/ with YAML front matter."""
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    filename = f"{_slugify(query)}_{now.strftime('%Y%m%d_%H%M%S')}.md"
    path = GENERATED_DIR / filename
    front_matter = (
        "---\n"
        f'date: "{now.strftime("%Y-%m-%d %H:%M:%S")}"\n'
        f'query: "{_yaml_escape(query)}"\n'
        f'trace_id: "{_yaml_escape(trace_id)}"\n'
        "---\n\n"
    )
    path.write_text(front_matter + markdown_report, encoding="utf-8")
    return path