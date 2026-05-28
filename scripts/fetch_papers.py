"""
Fetch relevant geoscience and meteorology papers from arXiv RSS feeds.

This script parses the arXiv daily RSS feeds for physics.ao-ph, physics.geo-ph,
and cs.LG categories, filters them using custom relevance heuristics
(whitelist/blacklist keyword scoring), and returns a balanced list of papers
across predefined topics.
"""

import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# RSS feed URLs (reliable, no rate-limiting)
RSS_FEEDS: List[str] = [
    "https://rss.arxiv.org/rss/physics.ao-ph",
    "https://rss.arxiv.org/rss/physics.geo-ph",
    "https://rss.arxiv.org/rss/cs.LG",
]

# Topics list
TOPICS: List[str] = [
    "Weather Forecasting",
    "Subseasonal to Seasonal Forecasting",
    "Climate Emulation",
    "Data Assimilation",
    "Downscaling",
]

# Maximum papers per category to ensure balance
MAX_PER_CATEGORY: int = 5

# RSS XML namespaces
_NS: Dict[str, str] = {
    "arxiv": "http://arxiv.org/schemas/atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def fetch_rss_feed(url: str, timeout: int = 20) -> Optional[str]:
    """
    Fetch the raw XML content of an arXiv RSS feed.

    Parameters
    ----------
    url : str
        The RSS feed URL to fetch.
    timeout : int, default 20
        HTTP request timeout in seconds.

    Returns
    -------
    str or None
        The raw XML string, or None if the request failed.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; pereza-blog/1.0; +https://github.com/pereza)"
        }
        import urllib.request

        req = urllib.request.Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except (URLError, HTTPError) as e:
        print(f"  Failed to fetch RSS feed {url}: {e}")
        return None


def parse_rss_items(xml_content: str) -> List[Dict[str, Any]]:
    """
    Parse arXiv RSS XML and extract paper items.

    Extracts title, abstract (description), link, authors, and publish date
    from each <item> element in the RSS channel.

    Parameters
    ----------
    xml_content : str
        The raw XML string of an arXiv RSS feed.

    Returns
    -------
    list[dict[str, Any]]
        A list of raw paper dictionaries with keys:
        'id', 'title', 'summary', 'link', 'authors', 'published'.
    """
    papers: List[Dict[str, Any]] = []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        print(f"  XML parse error: {e}")
        return papers

    channel = root.find("channel")
    if channel is None:
        return papers

    for item in channel.findall("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")
        guid_el = item.find("guid")

        if title_el is None or desc_el is None:
            continue

        title: str = (title_el.text or "").strip()
        link: str = (link_el.text or "").strip() if link_el is not None else ""

        # Extract paper ID from guid (format: oai:arXiv.org:XXXX.XXXXX[vN])
        arxiv_id: str = ""
        if guid_el is not None and guid_el.text:
            guid_text: str = guid_el.text.strip()
            if "arXiv.org:" in guid_text:
                raw_id = guid_text.split("arXiv.org:")[-1]
                # Strip version suffix if present
                arxiv_id = raw_id.split("v")[0] if "v" in raw_id else raw_id

        # Description contains "arXiv:XXXX.XXXXXvN Announce Type: new\nAbstract: ..."
        raw_desc: str = (desc_el.text or "").strip()
        # Strip the "arXiv:... Announce Type: ... Abstract:" header
        abstract: str = raw_desc
        if "Abstract:" in raw_desc:
            abstract = raw_desc.split("Abstract:", 1)[-1].strip()
        # Clean up whitespace
        abstract = " ".join(abstract.split())

        # Authors from dc:creator
        authors_el = item.find("dc:creator", _NS)
        authors: List[str] = []
        if authors_el is not None and authors_el.text:
            authors = [a.strip() for a in authors_el.text.split(",") if a.strip()]

        # Publication date from pubDate
        pub_date: str = ""
        pub_date_el = item.find("pubDate")
        if pub_date_el is not None and pub_date_el.text:
            # Convert "Thu, 28 May 2026 00:00:00 -0400" to "2026-05-28"
            try:
                from email.utils import parsedate

                parsed = parsedate(pub_date_el.text)
                if parsed:
                    pub_date = f"{parsed[0]:04d}-{parsed[1]:02d}-{parsed[2]:02d}"
            except Exception:
                pub_date = ""

        if not pub_date:
            from datetime import date

            pub_date = date.today().isoformat()

        if not title or not abstract:
            continue

        # Construct arXiv link if missing
        if not link and arxiv_id:
            link = f"https://arxiv.org/abs/{arxiv_id}"

        entry_id: str = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else link

        papers.append(
            {
                "id": entry_id,
                "title": title,
                "summary": abstract,
                "link": link,
                "authors": authors,
                "published": pub_date,
            }
        )

    return papers


def _has_word(text: str, word: str) -> bool:
    """
    Check if a word/phrase is present in the text as a whole word.

    Parameters
    ----------
    text : str
        The text to search.
    word : str
        The word or phrase to look for.

    Returns
    -------
    bool
        True if the word is found, False otherwise.
    """
    import re

    pattern: str = rf"\b{re.escape(word)}\b"
    return bool(re.search(pattern, text))


def _count_word(text: str, word: str) -> int:
    """
    Count the number of times a word/phrase occurs in the text as a whole word.

    Parameters
    ----------
    text : str
        The text to search.
    word : str
        The word or phrase to count.

    Returns
    -------
    int
        The count of occurrences.
    """
    import re

    pattern: str = rf"\b{re.escape(word)}\b"
    return len(re.findall(pattern, text))


def categorize_paper(
    title: str, summary: str, default_category: str = "Weather Forecasting"
) -> str:
    """
    Categorize a paper into one of the predefined geoscience topics.

    Analyses keyword occurrences in both the paper's title and summary
    to determine which topic is the best fit.

    Parameters
    ----------
    title : str
        The title of the paper.
    summary : str
        The abstract or summary of the paper.
    default_category : str, default "Weather Forecasting"
        The fallback category if no strong topic keywords match.

    Returns
    -------
    str
        The assigned category name from TOPICS.
    """
    text: str = (title + " " + summary).lower()

    scores: Dict[str, float] = {
        "Weather Forecasting": (
            _count_word(text, "weather forecast") * 3.0
            + _count_word(text, "weather prediction") * 3.0
            + _count_word(text, "nowcasting") * 2.5
            + _count_word(text, "precipitation forecast") * 2.0
            + _count_word(text, "numerical weather") * 2.5
            + _count_word(text, "nwp") * 2.0
            + _count_word(text, "forecasting") * 0.5
        ),
        "Subseasonal to Seasonal Forecasting": (
            _count_word(text, "subseasonal") * 3.0
            + _count_word(text, "seasonal forecast") * 3.0
            + _count_word(text, "s2s") * 3.0
            + _count_word(text, "seasonal prediction") * 3.0
            + _count_word(text, "interannual") * 2.0
            + _count_word(text, "el nino") * 2.0
            + _count_word(text, "enso") * 2.0
        ),
        "Climate Emulation": (
            _count_word(text, "emulator") * 3.0
            + _count_word(text, "emulation") * 3.0
            + _count_word(text, "climate model emulator") * 4.0
            + _count_word(text, "climate emulator") * 4.0
            + _count_word(text, "earth system model") * 2.5
            + _count_word(text, "coupled") * 1.5
            + _count_word(text, "cmip") * 2.0
            + _count_word(text, "gcm") * 2.0
        ),
        "Data Assimilation": (
            _count_word(text, "data assimilation") * 4.0
            + _count_word(text, "state estimation") * 2.0
            + _count_word(text, "kalman filter") * 2.5
            + _count_word(text, "variational") * 2.0
            + _count_word(text, "ensemble kalman") * 3.0
            + _count_word(text, "4dvar") * 3.0
            + _count_word(text, "3dvar") * 3.0
        ),
        "Downscaling": (
            _count_word(text, "downscaling") * 4.0
            + _count_word(text, "super-resolution") * 3.0
            + _count_word(text, "spatial resolution") * 2.0
            + _count_word(text, "temporal disaggregation") * 3.0
            + _count_word(text, "rainfall disaggregation") * 3.0
            + _count_word(text, "bias correction") * 2.5
            + _count_word(text, "bias adjustment") * 2.5
            + _count_word(text, "statistical downscaling") * 4.0
            + _count_word(text, "dynamical downscaling") * 4.0
        ),
    }

    best_category: str = default_category
    max_score: float = 0.0
    for topic, score in scores.items():
        if score > max_score:
            max_score = score
    return best_category


def is_relevant_geoscience(title: str, summary: str) -> bool:
    """
    Determine relevance of a paper to weather, climate, and geoscience.

    Computes a weighted score from positive and negative keyword occurrences
    in the title and abstract, and requires at least one core geoscience term
    to prevent general machine learning papers from matching.

    Parameters
    ----------
    title : str
        The title of the paper.
    summary : str
        The summary or abstract of the paper.

    Returns
    -------
    bool
        True if the paper is relevant to geoscience, False otherwise.
    """
    title_lower: str = title.lower()
    summary_lower: str = summary.lower()

    # Enforce at least one core geoscience keyword (as a whole word/phrase)
    core_keywords: List[str] = [
        "weather",
        "forecast",
        "forecasting",
        "nowcasting",
        "nwp",
        "climate",
        "climatology",
        "meteorology",
        "meteorological",
        "atmosphere",
        "atmospheric",
        "ocean",
        "oceanic",
        "sea surface",
        "sst",
        "sea ice",
        "downscaling",
        "downscale",
        "data assimilation",
        "precipitation",
        "rainfall",
        "temperature",
        "wind speed",
        "subseasonal",
        "seasonal",
        "s2s",
        "el nino",
        "enso",
        "monsoon",
        "cyclone",
        "hurricane",
        "flood",
        "drought",
        "reanalysis",
        "era5",
        "cerra",
        "cmip",
        "gcm",
        "earth system",
        "geoscience",
        "geophysical",
    ]

    has_core: bool = any(
        _has_word(title_lower, kw) or _has_word(summary_lower, kw)
        for kw in core_keywords
    )
    if not has_core:
        return False

    score: float = 0.0

    negatives: Dict[str, float] = {
        # Space weather & upper atmosphere
        "space weather": -10.0,
        "solar flare": -10.0,
        "radiation belt": -10.0,
        "solar wind": -10.0,
        "magnetosphere": -10.0,
        "ionosphere": -10.0,
        "coronal mass": -10.0,
        "geomagnetic": -8.0,
        # Medical & biological
        "retinopathy": -15.0,
        "medical imaging": -15.0,
        "clinical": -15.0,
        "biomedical": -15.0,
        "cancer": -15.0,
        "tumor": -15.0,
        "mri": -12.0,
        "ultrasound": -15.0,
        "cardiac": -15.0,
        "retinal": -15.0,
        "disease": -8.0,
        "pathology": -12.0,
        # Chemistry & materials science
        "interatomic": -12.0,
        "molecule": -10.0,
        "molecular dynamics": -12.0,
        "protein": -12.0,
        "drug": -12.0,
        "polymer": -12.0,
        "catalysis": -12.0,
        "nanoparticle": -12.0,
        "crystallography": -12.0,
        # Astronomy & high-energy physics
        "quantum": -8.0,
        "cosmology": -10.0,
        "galaxy": -10.0,
        "stellar": -10.0,
        "dark matter": -10.0,
        "black hole": -10.0,
        "astronomy": -10.0,
        "astrophysical": -10.0,
        # General ML not geoscience-related
        "reinforcement learning": -5.0,
        "natural language": -6.0,
        "text generation": -8.0,
        "large language model": -6.0,
        "llm": -8.0,
        "fraud detection": -15.0,
        "financial": -10.0,
        "stock market": -12.0,
        "sparse autoencoder": -10.0,
        "turing complete": -10.0,
        "federated learning": -6.0,
        "recommendation system": -10.0,
        "routing": -4.0,
        "token routing": -10.0,
        "social network": -10.0,
        "internet of things": -10.0,
        "iot": -8.0,
        "lunar rover": -15.0,
        "worker disagreement": -10.0,
        "graph neural": -3.0,
        "chain-of-thought": -15.0,
        "chain of thought": -15.0,
        "hopfield": -15.0,
        "liquid crystal": -12.0,
        "nematic": -12.0,
        "robot guide": -10.0,
        "tactile": -12.0,
        "proprioceptive": -12.0,
        "microcontroller": -10.0,
    }

    for keyword, penalty in negatives.items():
        if _has_word(title_lower, keyword):
            score += penalty * 1.5
        elif _has_word(summary_lower, keyword):
            score += penalty

    positives: Dict[str, float] = {
        # Core topics
        "weather forecast": 6.0,
        "weather forecasting": 6.0,
        "numerical weather prediction": 6.0,
        "nwp": 5.0,
        "climate emulation": 6.0,
        "climate emulator": 6.0,
        "model emulator": 5.0,
        "earth system model": 4.0,
        "subseasonal": 6.0,
        "seasonal forecast": 6.0,
        "s2s": 5.0,
        "downscaling": 6.0,
        "spatial downscaling": 6.0,
        "statistical downscaling": 6.0,
        "temporal downscaling": 6.0,
        "temporal disaggregation": 6.0,
        "rainfall disaggregation": 6.0,
        "bias correction": 5.0,
        "bias adjustment": 5.0,
        "super-resolution": 5.0,
        "postprocessing": 4.0,
        "data assimilation": 6.0,
        "state estimation": 4.0,
        "ensemble kalman": 6.0,
        "4dvar": 6.0,
        "3dvar": 6.0,
        # Methods
        "diffusion model": 3.0,
        "transformer": 2.5,
        "generative adversarial": 3.0,
        "unet": 2.0,
        "autoencoder": 2.0,
        "lstm": 2.0,
        # Meteorology / Climate terms
        "reanalysis": 4.0,
        "era5": 5.0,
        "cerra": 5.0,
        "nowcasting": 5.0,
        "precipitation": 3.0,
        "rainfall": 3.0,
        "monsoon": 4.0,
        "temperature": 2.0,
        "wind speed": 3.5,
        "el nino": 4.0,
        "enso": 4.0,
        "sea surface temperature": 4.0,
        "sst": 2.5,
        "climate change": 3.0,
        "climatology": 3.0,
        "meteorology": 4.0,
        "meteorological": 4.0,
        "atmosphere": 2.0,
        "atmospheric": 2.5,
        "oceanic": 2.0,
        "hydrology": 3.0,
        "hydrological": 3.0,
        "geoscience": 3.0,
        "geophysical": 3.0,
        "extreme precipitation": 5.0,
        "extreme events": 4.0,
        "flash flood": 5.0,
        "storm surge": 4.0,
        "drought": 3.0,
        "cordex": 4.0,
        "cmip6": 5.0,
        "gcm": 3.0,
        "sea ice": 4.0,
        "arctic": 3.0,
        "antarctic": 3.0,
        "tropical cyclone": 5.0,
        "hurricane": 4.0,
        "air quality": 4.0,
        "aerosol": 3.0,
        "deep learning": 1.0,
        "machine learning": 1.0,
        "neural network": 1.0,
    }

    for keyword, points in positives.items():
        if _has_word(title_lower, keyword):
            score += points * 2.0
        elif _has_word(summary_lower, keyword):
            score += points

    return score >= 5.0


def get_weekly_papers() -> List[Dict[str, Any]]:
    """
    Fetch and filter relevant geoscience papers from arXiv RSS feeds.

    Reads the daily RSS feeds for physics.ao-ph, physics.geo-ph, and cs.LG,
    filters them by geoscience relevance, classifies them by topic, and
    returns a balanced set (up to MAX_PER_CATEGORY per topic).

    Returns
    -------
    list[dict[str, Any]]
        A balanced, deduplicated list of categorized research papers.
    """
    all_papers_map: Dict[str, Dict[str, Any]] = {}

    for feed_url in RSS_FEEDS:
        print(f"Fetching RSS feed: {feed_url}")
        xml_content: Optional[str] = fetch_rss_feed(feed_url)
        if not xml_content:
            continue

        items: List[Dict[str, Any]] = parse_rss_items(xml_content)
        print(f"  Found {len(items)} items in feed")

        for paper in items:
            paper_id: str = paper["id"]
            if paper_id in all_papers_map:
                continue  # Already seen (cross-listed)

            title: str = paper["title"]
            summary: str = paper["summary"]

            if not is_relevant_geoscience(title, summary):
                continue

            cat: str = categorize_paper(title, summary)

            all_papers_map[paper_id] = {
                "id": paper_id.split("/abs/")[-1].replace("/", "_"),
                "title": title,
                "summary": summary[:400] + "..." if len(summary) > 400 else summary,
                "full_content": summary,
                "authors": paper["authors"],
                "link": paper["link"],
                "date": paper["published"],
                "category": cat,
                "type": "paper",
            }

        # Small delay between feeds to be polite
        time.sleep(1.0)

    # Balance: cap at MAX_PER_CATEGORY per topic
    from collections import defaultdict

    per_category: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for paper in all_papers_map.values():
        per_category[paper["category"]].append(paper)

    result_list: List[Dict[str, Any]] = []
    for cat in TOPICS:
        bucket = per_category.get(cat, [])
        # Sort by date descending, take top N
        bucket.sort(key=lambda x: x["date"], reverse=True)
        result_list.extend(bucket[:MAX_PER_CATEGORY])

    result_list.sort(key=lambda x: x["date"], reverse=True)
    return result_list


if __name__ == "__main__":
    papers_list: List[Dict[str, Any]] = get_weekly_papers()
    print(f"\nSuccessfully fetched {len(papers_list)} papers from arXiv RSS feeds.")
    from collections import Counter

    cat_counts = Counter(p["category"] for p in papers_list)
    for cat, count in sorted(cat_counts.items()):
        print(f"  {cat}: {count}")
