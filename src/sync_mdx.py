import os
import re
import datetime
import json
from src.paths import generated_root
from src.publishers.notion import query_published_pages, retrieve_page_markdown

def safe_slug(markdown: str, page_id: str) -> str:
    title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    title = title_match.group(1) if title_match else page_id
    
    cleaned = title.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", cleaned, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug if slug else page_id.replace("-", "")

def quote_yaml(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)

def sync_mdx() -> int:
    os.makedirs(generated_root, exist_ok=True)
    pages = query_published_pages()
    
    for page in pages:
        page_id = page.get("id")
        markdown = retrieve_page_markdown(page_id)
        
        title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        title = title_match.group(1) if title_match else page_id
        
        slug = safe_slug(markdown, page_id)
        
        iso_now = datetime.datetime.utcnow().isoformat() + "Z"
        output = [
            "---",
            f"title: {quote_yaml(title)}",
            f"slug: {quote_yaml(slug)}",
            f"notionPageId: {quote_yaml(page_id)}",
            f"syncedAt: {quote_yaml(iso_now)}",
            "---",
            "",
            markdown,
            ""
        ]
        
        file_path = generated_root / f"{slug}.mdx"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output))
            
    return len(pages)
