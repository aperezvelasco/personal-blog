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
    try:
        response: requests.Response = requests.get(url, timeout=15)
        if response.status_code != 200:
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
                " ".join(summary_elem.text.split()) if summary_elem is not None else ""
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
    except Exception as e:
        print(f"Error fetching papers for query '{query}': {e}")

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
    Check if a paper is relevant to climate and weather geosciences.

    Analyzes the title and summary for climate/weather-related terms
    and checks against a blacklist to avoid unrelated topics like chemistry,
    medicine, space science, and physics-only potentials.

    Parameters
    ----------
    title : str
        The title of the paper.
    summary : str
        The summary/abstract of the paper.

    Returns
    -------
    bool
        True if relevant, False otherwise.
    """
    text: str = (title + " " + summary).lower()

    # Blacklist keywords
    blacklist: List[str] = [
        "space weather",
        "solar flare",
        "radiation belt",
        "geomagnetic",
        "magnetosphere",
        "retinopathy",
        "medical",
        "interatomic",
        "molecule",
        "molecular",
        "materials science",
        "crystallography",
        "chemistry",
        "quantum chemistry",
        "astronomy",
        "cosmology",
        "galaxy",
        "stellar",
        "brain",
        "clinical",
        "biomedical",
        "polymer",
        "catalysis",
        "protein",
        "drug",
        "nanoparticle",
        "ionosphere",
        "coronal",
    ]

    for word in blacklist:
        if word in text:
            return False

    # Whitelist keywords
    whitelist: List[str] = [
        "weather",
        "climate",
        "climatology",
        "meteorology",
        "meteorological",
        "precipitation",
        "rainfall",
        "downscaling",
        "temperature",
        "forecast",
        "projection",
        "reanalysis",
        "wind",
        "monsoon",
        "el nino",
        "la nina",
        "sea surface temperature",
        "emulation",
        "emulator",
        "data assimilation",
        "nowcasting",
        "atmosphere",
        "atmospheric",
        "oceanic",
        "hydrology",
        "hydrological",
    ]

    return any(word in text for word in whitelist)


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
    # 1. Weather forecasting query
    q_weather: str = (
        'abs:"weather forecasting" AND '
        '(abs:"deep learning" OR abs:"machine learning" OR abs:"neural network")'
    )
    # 2. S2S forecasting query
    q_s2s: str = (
        '(abs:"subseasonal" OR abs:"seasonal forecast") AND '
        '(abs:"deep learning" OR abs:"machine learning" OR abs:"neural network")'
    )
    # 3. Climate emulation query
    q_emulation: str = (
        '(abs:"climate emulation" OR abs:"climate emulator" OR abs:"model emulator") '
        'AND (abs:"deep learning" OR abs:"machine learning" OR abs:"neural network")'
    )
    # 4. Data Assimilation query
    q_assimilation: str = (
        'abs:"data assimilation" AND '
        '(abs:"deep learning" OR abs:"machine learning" OR abs:"neural network")'
    )
    # 5. Downscaling query
    q_downscaling: str = (
        'abs:"downscaling" AND '
        '(abs:"deep learning" OR abs:"machine learning" OR abs:"neural network")'
    )

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
        time.sleep(3)

    # Convert map to list and sort by date descending
    result_list: List[Dict[str, Any]] = list(all_papers_map.values())
    result_list.sort(key=lambda x: x["date"], reverse=True)
    return result_list


if __name__ == "__main__":
    # Test script directly
    papers_list: List[Dict[str, Any]] = get_weekly_papers()
    print(f"Successfully fetched {len(papers_list)} papers from arXiv.")
