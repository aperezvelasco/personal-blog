"""
Fetch relevant geoscience and meteorology papers from the arXiv API.

This script queries arXiv for papers on specific weather, climate, and downscaling
topics, filters them using custom relevance heuristics (e.g. whitelist/blacklist),
and returns the compiled list of papers.
"""

import time
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import requests

# Topics list
TOPICS: List[str] = [
    "Weather Forecasting",
    "Subseasonal to Seasonal Forecasting",
    "Climate Emulation",
    "Data Assimilation",
    "Downscaling",
]


def fetch_arxiv_papers(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """
    Fetch papers from arXiv API for a given search query.

    Queries the arXiv API syndication XML feed and extracts details of
    the matching papers, returning a list of structured dictionaries.
    Includes a retry mechanism with backoff for transient timeouts.

    Parameters
    ----------
    query : str
        The arXiv-formatted search query string.
    max_results : int, default 15
        The maximum number of results to fetch for this query.

    Returns
    -------
    list[dict[str, Any]]
        A list of paper dictionaries, each containing 'id', 'title', 'summary',
        'published', 'authors', and 'link'.
    """
    base_url: str = "http://export.arxiv.org/api/query"
    params: Dict[str, str] = {
        "search_query": query,
        "max_results": str(max_results),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url: str = f"{base_url}?{urllib.parse.urlencode(params)}"

    papers: List[Dict[str, Any]] = []

    max_retries: int = 3
    timeout_seconds: float = 25.0

    for attempt in range(max_retries):
        try:
            response: requests.Response = requests.get(url, timeout=timeout_seconds)

            # If rate limited (503 or 429), wait and retry
            if response.status_code in (503, 429):
                wait_time: float = 8.0 * (attempt + 1)
                print(
                    f"arXiv API returned {response.status_code}. "
                    f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
                continue

            if response.status_code != 200:
                print(
                    f"arXiv API returned status code {response.status_code} "
                    f"for query '{query[:40]}...'"
                )
                return papers

            root: ET.Element = ET.fromstring(response.content)
            # XML namespace for Atom feed
            ns: Dict[str, str] = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                # Extract id
                paper_id_elem: Optional[ET.Element] = entry.find("atom:id", ns)
                paper_id: str = (
                    paper_id_elem.text.strip() if paper_id_elem is not None else ""
                )

                # Extract title and clean whitespace
                title_elem: Optional[ET.Element] = entry.find("atom:title", ns)
                title: str = (
                    " ".join(title_elem.text.split())
                    if title_elem is not None
                    else "No Title"
                )

                # Extract summary (abstract)
                summary_elem: Optional[ET.Element] = entry.find("atom:summary", ns)
                summary: str = (
                    " ".join(summary_elem.text.split())
                    if summary_elem is not None
                    else ""
                )

                # Extract published date
                published_elem: Optional[ET.Element] = entry.find("atom:published", ns)
                published: str = (
                    published_elem.text.strip() if published_elem is not None else ""
                )

                # Extract authors
                authors: List[str] = []
                for author in entry.findall("atom:author", ns):
                    name_elem: Optional[ET.Element] = author.find("atom:name", ns)
                    if name_elem is not None:
                        authors.append(name_elem.text.strip())

                # Extract primary alternate link
                link: str = paper_id
                for link_elem in entry.findall("atom:link", ns):
                    if link_elem.attrib.get("rel") == "alternate":
                        link = link_elem.attrib.get("href", link)
                        break

                papers.append(
                    {
                        "id": paper_id,
                        "title": title,
                        "summary": summary,
                        "published": published,
                        "authors": authors,
                        "link": link,
                    }
                )

            # If successful, break retry loop
            break

        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                print(
                    f"Error fetching papers for query '{query[:60]}...': "
                    f"{e} after {max_retries} attempts"
                )
            else:
                wait_time = 3.0 * (attempt + 1)
                print(
                    f"Request failed/timed out for query '{query[:40]}...'. "
                    f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)

    return papers


def categorize_paper(title: str, summary: str) -> str:
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

    Returns
    -------
    str
        The assigned category name from TOPICS.
    """
    text: str = (title + " " + summary).lower()

    # Topic keywords matching
    scores: Dict[str, int] = {
        "Weather Forecasting": text.count("weather forecast")
        + text.count("weather prediction")
        + text.count("forecasting") * 0.5,
        "Subseasonal to Seasonal Forecasting": text.count("subseasonal")
        + text.count("seasonal forecasting")
        + text.count("s2s"),
        "Climate Emulation": text.count("emulator")
        + text.count("emulation")
        + text.count("climate model emulator"),
        "Data Assimilation": text.count("data assimilation")
        + text.count("state estimation"),
        "Downscaling": text.count("downscaling")
        + text.count("super-resolution")
        + text.count("spatial resolution"),
    }

    # Pick the category with the highest non-zero score,
    # defaulting to "Weather Forecasting".
    best_category: str = "Weather Forecasting"
    max_score: float = 0.0
    for topic, score in scores.items():
        if score > max_score:
            max_score = score
            best_category = topic

    return best_category


def is_relevant_geoscience(title: str, summary: str) -> bool:
    """
    Determine relevance of a paper using a weighted scoring engine.

    Computes a score based on positive and negative keyword occurrences in
    the title and abstract (summary), giving higher weight to title matches.
    The paper is considered relevant if the final score exceeds a threshold.

    Parameters
    ----------
    title : str
        The title of the paper.
    summary : str
        The summary/abstract of the paper.

    Returns
    -------
    bool
        True if the score is above the threshold, False otherwise.
    """
    title_lower: str = title.lower()
    summary_lower: str = summary.lower()

    score: float = 0.0

    # 1. Negative keywords (immediate penalty, can quickly drive score below threshold)
    negatives: Dict[str, float] = {
        # Space weather & upper atmosphere
        "space weather": -10.0,
        "solar flare": -10.0,
        "radiation belt": -10.0,
        "solar wind": -10.0,
        "magnetosphere": -10.0,
        "ionosphere": -10.0,
        "coronal mass": -10.0,
        "geomagnetic": -10.0,
        # Medical & biological
        "retinopathy": -15.0,
        "medical": -15.0,
        "clinical": -15.0,
        "biomedical": -15.0,
        "brain": -15.0,
        "cancer": -15.0,
        "tumor": -15.0,
        "mri": -15.0,
        "ultrasound": -15.0,
        "cardiac": -15.0,
        "retinal": -15.0,
        "disease": -10.0,
        # Chemistry & materials science
        "interatomic": -12.0,
        "molecule": -12.0,
        "molecular": -12.0,
        "protein": -12.0,
        "drug": -12.0,
        "polymer": -12.0,
        "catalysis": -12.0,
        "materials science": -12.0,
        "crystallography": -12.0,
        "nanoparticle": -12.0,
        # Astronomy & high-energy physics
        "quantum": -10.0,
        "cosmology": -10.0,
        "galaxy": -10.0,
        "stellar": -10.0,
        "dark matter": -10.0,
        "black hole": -10.0,
        "astronomy": -10.0,
        "astrophysical": -10.0,
    }

    for keyword, penalty in negatives.items():
        if keyword in title_lower:
            score += penalty * 1.5
        if keyword in summary_lower:
            score += penalty

    # 2. Positive keywords (adds relevance points)
    positives: Dict[str, float] = {
        # Core topics
        "weather forecast": 5.0,
        "weather forecasting": 5.0,
        "numerical weather prediction": 5.0,
        "nwp": 4.0,
        "climate emulation": 5.0,
        "climate emulator": 5.0,
        "model emulator": 4.0,
        "climate model": 3.0,
        "subseasonal": 5.0,
        "seasonal forecast": 5.0,
        "s2s": 4.0,
        "downscaling": 5.0,
        "spatial downscaling": 5.0,
        "statistical downscaling": 5.0,
        "data assimilation": 5.0,
        "state estimation": 3.0,
        # Supporting meteorology / climate concepts
        "reanalysis": 4.0,
        "era5": 4.0,
        "cams": 3.0,
        "nowcasting": 4.0,
        "precipitation nowcasting": 4.0,
        "precipitation": 3.0,
        "rainfall": 3.0,
        "monsoon": 3.0,
        "temperature": 2.0,
        "wind speed": 3.0,
        "el nino": 3.0,
        "sea surface temperature": 4.0,
        "sst": 2.0,
        "climate change": 3.0,
        "climatology": 3.0,
        "meteorology": 3.0,
        "meteorological": 3.0,
        "atmosphere": 2.0,
        "atmospheric": 2.0,
        "oceanic": 2.0,
        "hydrology": 2.0,
        "hydrological": 2.0,
        "geoscience": 2.0,
        "geoscientific": 2.0,
        # Machine Learning indicators
        "deep learning": 1.0,
        "machine learning": 1.0,
        "neural network": 1.0,
        "neural networks": 1.0,
    }

    for keyword, points in positives.items():
        if keyword in title_lower:
            score += points * 2.0  # title matches are more significant
        if keyword in summary_lower:
            score += points

    # Threshold for relevance
    # A paper must gather at least 4.0 points to be considered geoscience-relevant.
    return score >= 4.0


def get_weekly_papers() -> List[Dict[str, Any]]:
    """
    Run search queries for all topics and aggregate results.

    Queries arXiv for each of the 5 geoscience topics, classifies the papers,
    deduplicates them, and returns a unified list sorted by publication date.

    Returns
    -------
    list[dict[str, Any]]
        Deduplicated list of categorized research papers.
    """
    category_filter: str = (
        "(cat:physics.ao-ph OR cat:physics.geo-ph OR cat:cs.LG OR cat:stat.ML)"
    )

    ml_filter: str = (
        '("deep learning" OR "machine learning" OR '
        '"neural network" OR "neural networks")'
    )

    # 1. Weather forecasting query
    q_weather: str = (
        f"{category_filter} AND "
        '("weather forecasting" OR "numerical weather prediction" OR '
        '"weather forecast") '
        f"AND {ml_filter}"
    )
    # 2. S2S forecasting query
    q_s2s: str = (
        f"{category_filter} AND "
        '("subseasonal" OR "seasonal forecast" OR "s2s") '
        f"AND {ml_filter}"
    )
    # 3. Climate emulation query
    q_emulation: str = (
        f"{category_filter} AND "
        '("climate emulation" OR "climate emulator" OR "model emulator") '
        f"AND {ml_filter}"
    )
    # 4. Data Assimilation query
    q_assimilation: str = (
        f"{category_filter} AND " f'"data assimilation" AND {ml_filter}'
    )
    # 5. Downscaling query
    q_downscaling: str = f"{category_filter} AND " f'"downscaling" AND {ml_filter}'

    queries: Dict[str, str] = {
        "Weather Forecasting": q_weather,
        "Subseasonal to Seasonal Forecasting": q_s2s,
        "Climate Emulation": q_emulation,
        "Data Assimilation": q_assimilation,
        "Downscaling": q_downscaling,
    }

    all_papers_map: Dict[str, Dict[str, Any]] = {}

    for default_category, query in queries.items():
        print(f"Fetching papers for query: {query}")
        fetched: List[Dict[str, Any]] = fetch_arxiv_papers(query, max_results=10)

        for paper in fetched:
            # Check relevance to weather and climate
            if not is_relevant_geoscience(paper["title"], paper["summary"]):
                print(f"Skipping unrelated paper: {paper['title']}")
                continue

            # Let's perform refined classification based on content
            cat: str = categorize_paper(paper["title"], paper["summary"])
            # If the refined category gets 0 score, fallback to default_category
            title_summary_lower: str = (paper["title"] + " " + paper["summary"]).lower()
            if cat == "Weather Forecasting" and "weather" not in title_summary_lower:
                cat = default_category

            paper_id: str = paper["id"]
            if paper_id not in all_papers_map:
                # Structure the post like a blog post
                all_papers_map[paper_id] = {
                    "id": paper_id.split("/abs/")[-1].replace("/", "_"),
                    "title": paper["title"],
                    "summary": (
                        paper["summary"][:350] + "..."
                        if len(paper["summary"]) > 350
                        else paper["summary"]
                    ),
                    "full_content": paper["summary"],
                    "authors": paper["authors"],
                    "link": paper["link"],
                    "date": paper["published"][:10],  # YYYY-MM-DD
                    "category": cat,
                    "type": "paper",
                }
        # Sleep to comply with arXiv API etiquette
        time.sleep(4)

    # Convert map to list and sort by date descending
    result_list: List[Dict[str, Any]] = list(all_papers_map.values())
    result_list.sort(key=lambda x: x["date"], reverse=True)
    return result_list


if __name__ == "__main__":
    # Test script directly
    papers_list: List[Dict[str, Any]] = get_weekly_papers()
    print(f"Successfully fetched {len(papers_list)} papers from arXiv.")
