"""
Add a new paper entry to the blog database (data/posts.json).

This script formats the paper details, generates a plain-language explanation
using the Gemini API (if key is available), and appends/updates the paper
entry in data/posts.json.
"""

import argparse
import json
import os
import sys
from datetime import date
from typing import Any, Dict, List, Optional

# Ensure current directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generate_explanation import generate_paper_explanation


def add_paper(
    title: str,
    abstract: str,
    authors: List[str],
    link: str,
    date_str: str,
    category: str,
    explanation: Optional[str] = None,
) -> None:
    """
    Format and add a research paper to the posts database.

    Parameters
    ----------
    title : str
        The original title of the paper.
    abstract : str
        The full abstract or summary of the paper.
    authors : list[str]
        List of authors who wrote the paper.
    link : str
        The arXiv URL or link to the paper.
    date_str : str
        The publication date in YYYY-MM-DD format.
    category : str
        The blog category assigned to the paper.
    explanation : str, optional
        Pre-generated markdown explanation. If not provided, it will be
        generated using the Gemini API.
    """
    project_root: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir: str = os.path.join(project_root, "data")
    posts_file: str = os.path.join(data_dir, "posts.json")

    os.makedirs(data_dir, exist_ok=True)

    # Load existing posts
    posts: List[Dict[str, Any]] = []
    if os.path.exists(posts_file):
        try:
            with open(posts_file, "r", encoding="utf-8") as f:
                posts = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load existing posts: {e}")

    # Extract paper ID from link or title
    paper_id: str = (
        link.split("/abs/")[-1].replace("/", "_")
        if "/abs/" in link
        else title.lower().replace(" ", "-")
    )

    # Generate explanation if not provided
    if not explanation:
        print(
            f"Generating plain-language explanation for '{title}' " "via Gemini API..."
        )
        generated, daily_exhausted = generate_paper_explanation(
            title=title,
            abstract=abstract,
            authors=authors,
            category=category,
        )
        if daily_exhausted or not generated:
            print(
                "Warning: Could not generate explanation via API. "
                "Please provide a pre-generated explanation."
            )
            explanation = ""
        else:
            explanation = generated.strip()

    # Create new paper entry
    new_paper: Dict[str, Any] = {
        "id": paper_id,
        "title": title,
        "summary": abstract[:400] + "..." if len(abstract) > 400 else abstract,
        "full_content": abstract,
        "authors": authors,
        "link": link,
        "date": date_str,
        "category": category,
        "type": "paper",
        "explanation": explanation,
    }

    # Remove any existing duplicate entries
    posts = [
        p
        for p in posts
        if p.get("id") != paper_id
        and p.get("title") != title
        and p.get("id") != f"explanation-{paper_id}"
    ]

    posts.append(new_paper)

    # Sort all posts by date descending
    posts.sort(key=lambda x: x.get("date", ""), reverse=True)

    with open(posts_file, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"✓ Successfully added paper '{title}' to {posts_file}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a paper to the blog database.")
    parser.add_argument("--title", required=True, help="Title of the paper")
    parser.add_argument(
        "--abstract", required=True, help="Abstract/summary of the paper"
    )
    parser.add_argument(
        "--authors", required=True, help="Comma-separated list of authors"
    )
    parser.add_argument("--link", required=True, help="Link to the paper")
    parser.add_argument(
        "--date", default=date.today().isoformat(), help="Publish date (YYYY-MM-DD)"
    )
    parser.add_argument("--category", required=True, help="Category of the paper")
    parser.add_argument(
        "--explanation-file",
        help="Path to a file containing the pre-generated explanation",
    )

    args = parser.parse_args()

    authors_list: List[str] = [a.strip() for a in args.authors.split(",") if a.strip()]

    pre_explanation: Optional[str] = None
    if args.explanation_file:
        try:
            with open(args.explanation_file, "r", encoding="utf-8") as f:
                pre_explanation = f.read()
        except Exception as e:
            print(f"Error reading explanation file: {e}")
            sys.exit(1)

    add_paper(
        title=args.title,
        abstract=args.abstract,
        authors=authors_list,
        link=args.link,
        date_str=args.date,
        category=args.category,
        explanation=pre_explanation,
    )
