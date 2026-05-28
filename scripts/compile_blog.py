"""
Compile blog posts and fetched papers into a single JSON database.

This script reads manual blog posts (Markdown format) from the content
directory, fetches relevant weekly geoscience papers from the arXiv RSS feeds,
optionally generates plain-language explanations using the Gemini API,
merges everything chronologically, and saves to data/posts.json.
"""

import json
import os
import sys
from typing import Any, Dict, List

import frontmatter
import markdown

# Ensure current directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fetch_papers import get_weekly_papers
from generate_explanation import enrich_papers_with_explanations


def parse_markdown_posts(content_dir: str) -> List[Dict[str, Any]]:
    """
    Parse manual markdown blog posts from the specified directory.

    Reads all markdown (.md) files in the directory, parses their
    YAML frontmatter, converts their markdown body to HTML, and returns
    them as a list of dictionaries.

    Parameters
    ----------
    content_dir : str
        The directory path containing the markdown files.

    Returns
    -------
    list[dict[str, Any]]
        A list of blog post dictionaries containing parsed metadata and HTML body.
    """
    posts: List[Dict[str, Any]] = []
    if not os.path.exists(content_dir):
        return posts

    for filename in os.listdir(content_dir):
        if filename.endswith(".md"):
            file_path: str = os.path.join(content_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    post = frontmatter.load(f)

                # Convert markdown body to HTML
                html_content: str = markdown.markdown(
                    post.content,
                    extensions=["fenced_code", "tables"],
                )

                post_data: Dict[str, Any] = {
                    "id": filename.replace(".md", ""),
                    "title": post.get("title", "Untitled Post"),
                    "summary": post.get("summary", ""),
                    "full_content": html_content,
                    "authors": post.get("authors", ["Antonio Pérez Velasco"]),
                    "link": post.get("link", ""),
                    "date": str(post.get("date", "")),
                    "category": post.get("category", "Blog"),
                    "type": "blog",
                }
                posts.append(post_data)
            except Exception as e:
                print(f"Error parsing manual post {filename}: {e}")

    return posts


def load_cached_papers(output_file: str) -> List[Dict[str, Any]]:
    """
    Load previously compiled paper entries from the JSON database.

    Parameters
    ----------
    output_file : str
        Path to the existing posts.json file.

    Returns
    -------
    list[dict[str, Any]]
        List of paper entries from the cached file, or empty list if unavailable.
    """
    if not os.path.exists(output_file):
        return []
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            existing_posts: List[Dict[str, Any]] = json.load(f)
        return [p for p in existing_posts if p.get("type") == "paper"]
    except Exception as e:
        print(f"Warning: Could not load cached papers from {output_file}: {e}")
        return []


def compile_all_posts() -> None:
    """
    Orchestrate fetching arXiv papers and parsing manual blog posts.

    Combines both sets of posts, optionally enriches paper entries with
    AI-generated plain-language explanations (if GEMINI_API_KEY is set),
    sorts them chronologically in descending order, and saves the resulting
    array into 'data/posts.json'.
    """
    project_root: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    content_dir: str = os.path.join(project_root, "content")
    data_dir: str = os.path.join(project_root, "data")
    output_file: str = os.path.join(data_dir, "posts.json")

    os.makedirs(content_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    # --- 1. Parse manual blog posts ---
    print("Parsing manual blog posts...")
    manual_posts: List[Dict[str, Any]] = parse_markdown_posts(content_dir)
    print(f"Found {len(manual_posts)} manual blog posts.")

    # --- 2. Fetch papers from arXiv RSS ---
    print("\nFetching weekly papers from arXiv RSS feeds...")
    papers: List[Dict[str, Any]] = get_weekly_papers()
    print(f"Successfully fetched {len(papers)} papers.")

    # Load cached papers if fetch returned nothing
    if not papers:
        print("arXiv RSS returned no papers. Restoring cached papers...")
        papers = load_cached_papers(output_file)
        if papers:
            print(f"Restored {len(papers)} cached papers.")

    # --- 3. Merge with existing cached papers (preserve explanations) ---
    # Build index of existing papers to preserve their explanations
    cached_map: Dict[str, Dict[str, Any]] = {}
    for p in load_cached_papers(output_file):
        cached_map[p.get("id", "")] = p

    # Carry forward existing explanations so we don't regenerate them
    merged_papers: List[Dict[str, Any]] = []
    for paper in papers:
        pid = paper.get("id", "")
        if pid in cached_map and cached_map[pid].get("explanation"):
            paper = {**paper, "explanation": cached_map[pid]["explanation"]}
        merged_papers.append(paper)

    # --- 4. Generate plain-language explanations via Gemini ---
    print("\nGenerating plain-language explanations for papers...")
    merged_papers = enrich_papers_with_explanations(merged_papers)

    # --- 5. Combine and sort all posts ---
    all_posts: List[Dict[str, Any]] = manual_posts + merged_papers
    all_posts.sort(key=lambda x: x["date"], reverse=True)

    # --- 6. Save to file ---
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, indent=2, ensure_ascii=False)

    print(
        f"\n✓ Blog compiled successfully. Total posts: {len(all_posts)} "
        f"({len(manual_posts)} manual + {len(merged_papers)} papers). "
        f"Saved to {output_file}"
    )

    # Print category breakdown
    from collections import Counter

    cat_counts: Counter = Counter(p.get("category", "?") for p in merged_papers)
    print("\nPaper category breakdown:")
    for cat, count in sorted(cat_counts.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    compile_all_posts()
