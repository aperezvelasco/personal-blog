import json
import os
import sys
from typing import Any, Dict, List
import frontmatter
import markdown

# Ensure current directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fetch_papers import get_weekly_papers

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
                html_content: str = markdown.markdown(post.content)
                
                # Build post dict
                post_data: Dict[str, Any] = {
                    "id": filename.replace(".md", ""),
                    "title": post.get("title", "Untitled Post"),
                    "summary": post.get("summary", ""),
                    "full_content": html_content,
                    "authors": post.get("authors", ["Antonio Pérez Velasco"]),
                    "link": post.get("link", ""),
                    "date": str(post.get("date", "")),
                    "category": post.get("category", "Blog"),
                    "type": "blog"
                }
                posts.append(post_data)
            except Exception as e:
                print(f"Error parsing manual post {filename}: {e}")
                
    return posts

def compile_all_posts() -> None:
    """
    Orchestrate fetching arXiv papers and parsing manual blog posts.

    Combines both sets of posts, sorts them chronologically in descending
    order, and saves the resulting array into 'data/posts.json'.
    """
    project_root: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    content_dir: str = os.path.join(project_root, "content")
    data_dir: str = os.path.join(project_root, "data")
    output_file: str = os.path.join(data_dir, "posts.json")
    
    # Create directories if they don't exist
    os.makedirs(content_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    print("Parsing manual blog posts...")
    manual_posts: List[Dict[str, Any]] = parse_markdown_posts(content_dir)
    print(f"Found {len(manual_posts)} manual blog posts.")
    
    print("Fetching weekly papers from arXiv...")
    papers: List[Dict[str, Any]] = get_weekly_papers()
    print(f"Successfully fetched {len(papers)} papers.")
    
    # Combine posts
    all_posts: List[Dict[str, Any]] = manual_posts + papers
    
    # Sort posts by date descending
    all_posts.sort(key=lambda x: x["date"], reverse=True)
    
    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, indent=2, ensure_ascii=False)
        
    print(f"Blog compiled successfully. Total posts: {len(all_posts)}. Saved to {output_file}")

if __name__ == "__main__":
    compile_all_posts()
