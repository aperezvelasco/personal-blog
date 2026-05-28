"""
Generate plain-language, didactic explanations for arXiv papers using the Gemini API.

This module uses the google-genai SDK to generate educational 3-5 minute
blog-style reads from paper titles and abstracts, using the Gemini Flash model.
The GEMINI_API_KEY (or GOOGLE_API_KEY) must be available as an environment
variable or in a .env file at the project root.

Free-tier note: the free-tier key is limited to ~15 RPM. This module respects
the retryDelay from 429 errors and spaces calls accordingly.
"""

import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# lighter model → lower token cost / rate limits
_MODEL_ID = "gemini-2.0-flash-lite"

# Detailed prompt to generate long, high-quality reads
_EXPLANATION_PROMPT = """\
You are a science communicator.
Write a plain-language blog post (5–10 min read)
explaining this arXiv paper to a non-expert reader.

Title: {title}
Category: {category}
Abstract: {abstract}

Rules:
- Use clear, jargon-free English (explain any technical terms).
- Structure: intro hook → problem → approach → results → key takeaways.
- Include one Mermaid diagram (```mermaid```) if helpful.
- End with "## Key Takeaways" bullet list (3–5 bullets).
- No YAML front matter. No opening "Here is...". Start directly.
- ~1000 words.
"""

# Delay between consecutive API calls (free tier: 15 RPM → 4s min)
_INTER_CALL_DELAY: float = 6.0

# Max delay to honor from a 429 response before giving up
_MAX_RATE_LIMIT_WAIT: float = 65.0


def _load_dotenv() -> None:
    """
    Load environment variables from a .env file at the project root if present.

    Searches from the script directory upwards for a .env file and populates
    os.environ with its key-value pairs, without overwriting existing values.
    """
    script_dir = Path(__file__).parent
    for parent in [script_dir, script_dir.parent]:
        env_file = parent / ".env"
        if env_file.exists():
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key not in os.environ:
                                os.environ[key] = value
            except Exception as e:
                print(f"  Warning: Could not read .env file: {e}")
            break


def _get_api_key() -> Optional[str]:
    """
    Retrieve the Gemini API key from environment variables or .env file.

    Returns
    -------
    str or None
        The API key string, or None if not found.
    """
    _load_dotenv()
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def _parse_retry_delay(error_message: str) -> float:
    """
    Extract the suggested retry delay (in seconds) from a 429 error message.

    Looks for patterns like "Please retry in 21.3s" or "retryDelay: '21s'" in
    the error string and returns the numeric value.

    Parameters
    ----------
    error_message : str
        The error message string from a 429 API response.

    Returns
    -------
    float
        The suggested wait time in seconds, defaulting to 30.0 if not found.
    """
    # Pattern: "Please retry in 21.3s" or "retry in 21s"
    match = re.search(r"retry[^\d]*(\d+(?:\.\d+)?)\s*s", error_message, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 2.0  # small buffer
    # Pattern: retryDelay: '21s'
    match = re.search(r"retryDelay['\": ]+(\d+)", error_message, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 2.0
    return 30.0


class _DailyQuotaExhausted(Exception):
    """Raised when the Gemini daily quota is fully exhausted."""

    pass


def _is_daily_quota_error(err_str: str) -> bool:
    """
    Return True if the error indicates a daily (not per-minute) quota exhaustion.

    Parameters
    ----------
    err_str : str
        The string representation of the API exception.

    Returns
    -------
    bool
        True if the daily quota is exhausted.
    """
    return "PerDay" in err_str or "per_day" in err_str.lower()


def _generate_via_sdk(api_key: str, prompt: str) -> Optional[str]:
    """
    Generate text using the google-genai SDK with rate-limit-aware retries.

    On a per-minute 429, waits the suggested retryDelay and retries.
    On a daily quota 429, raises _DailyQuotaExhausted immediately.

    Parameters
    ----------
    api_key : str
        The Gemini API key.
    prompt : str
        The full prompt text.

    Returns
    -------
    str or None
        The generated text, or None on transient failure.

    Raises
    ------
    _DailyQuotaExhausted
        If the daily API quota has been fully exhausted.
    """
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        print("    google-genai not installed. Run: pixi add google-genai")
        return None

    client = genai.Client(api_key=api_key)

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=_MODEL_ID,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=4000,
                ),
            )
            return response.text

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                # Daily quota exhausted — no point retrying
                if _is_daily_quota_error(err_str):
                    raise _DailyQuotaExhausted(
                        "Daily Gemini API quota exhausted. Explanations will be "
                        "generated on the next run."
                    )
                # Per-minute limit — wait and retry
                wait = _parse_retry_delay(err_str)
                if wait > _MAX_RATE_LIMIT_WAIT:
                    print(f"    Rate limit wait {wait:.0f}s too long. Skipping.")
                    return None
                print(f"    Rate limited ({wait:.0f}s). Retry {attempt + 1}/2...")
                time.sleep(wait)
            else:
                print(f"    SDK error: {e}")
                return None

    return None


def generate_paper_explanation(
    title: str,
    abstract: str,
    authors: List[str],
    category: str,
) -> Tuple[Optional[str], bool]:
    """
    Generate a plain-language explanation for an arXiv paper using the Gemini API.

    Uses _generate_via_sdk with rate-limit-aware retries. Returns a tuple of
    (explanation_text, daily_quota_exhausted). If the daily quota is hit,
    returns (None, True) so callers can stop trying immediately.

    Parameters
    ----------
    title : str
        The paper's title.
    abstract : str
        The paper's full abstract/summary.
    authors : list[str]
        The list of author names.
    category : str
        The blog category assigned to the paper.

    Returns
    -------
    tuple[str or None, bool]
        (generated_text, daily_quota_exhausted). Text is None on failure.
    """
    api_key: Optional[str] = _get_api_key()
    if not api_key:
        return None, False

    # Truncate abstract to ~800 chars to stay within token budget
    abstract_truncated: str = (
        abstract[:800] + "..." if len(abstract) > 800 else abstract
    )

    prompt: str = _EXPLANATION_PROMPT.format(
        title=title,
        category=category,
        abstract=abstract_truncated,
    )

    try:
        result = _generate_via_sdk(api_key, prompt)
        return result, False
    except _DailyQuotaExhausted as e:
        print(f"    ⚠ {e}")
        return None, True


def enrich_papers_with_explanations(
    papers: List[Dict[str, Any]],
    force_regenerate: bool = False,
) -> List[Dict[str, Any]]:
    """
    Add a plain-language 'explanation' field to each paper in the list.

    Skips papers that already have an 'explanation' field (unless
    force_regenerate is True). Only processes entries with type 'paper'.
    Applies a polite inter-call delay to respect API rate limits.

    Parameters
    ----------
    papers : list[dict[str, Any]]
        List of paper dicts with at least 'title', 'full_content', 'authors',
        and 'category' fields.
    force_regenerate : bool, default False
        If True, regenerates explanations even for papers that already have one.

    Returns
    -------
    list[dict[str, Any]]
        The same list, with 'explanation' field added or updated on paper entries.
    """
    api_key: Optional[str] = _get_api_key()

    if not api_key:
        print(
            "  Warning: No GEMINI_API_KEY found. Skipping explanation generation.\n"
            "  To enable: create a .env file in the project root with:\n"
            "    GEMINI_API_KEY=your_key_here\n"
            "  Or set it as a GitHub Actions secret named GEMINI_API_KEY."
        )
        return papers

    enriched: List[Dict[str, Any]] = []
    paper_items = [(i, p) for i, p in enumerate(papers) if p.get("type") == "paper"]
    paper_count = len(paper_items)
    paper_index = 0

    for orig_index, paper in enumerate(papers):
        if paper.get("type") != "paper":
            enriched.append(paper)
            continue

        paper_index += 1

        if not force_regenerate and paper.get("explanation"):
            print(
                f"  [{paper_index}/{paper_count}] "
                f"Skipping (already explained): {paper['title'][:60]}"
            )
            enriched.append(paper)
            continue

        print(f"  [{paper_index}/{paper_count}] " f"Explaining: {paper['title'][:60]}")

        explanation, daily_exhausted = generate_paper_explanation(
            title=paper["title"],
            abstract=paper.get("full_content", paper.get("summary", "")),
            authors=paper.get("authors", []),
            category=paper.get("category", "Weather Forecasting"),
        )

        if daily_exhausted:
            # Daily quota is gone — stop trying, just append remaining as-is
            print("  ⚠ Daily quota exhausted. Skipping remaining explanations.")
            enriched.append(paper)
            # Append all papers that come after this one in the original list
            for remaining in papers[orig_index + 1 :]:
                enriched.append(remaining)
            break

        if explanation:
            paper = {**paper, "explanation": explanation.strip()}
            print(f"    ✓ Generated ({len(explanation)} chars)")
        else:
            print("    ✗ Skipped")

        enriched.append(paper)

        # Polite delay between calls to respect free-tier rate limits
        if paper_index < paper_count:
            time.sleep(_INTER_CALL_DELAY)

    explained = sum(
        1 for p in enriched if p.get("type") == "paper" and p.get("explanation")
    )
    print(f"\n  Explanations: {explained}/{paper_count} papers enriched.")
    return enriched
