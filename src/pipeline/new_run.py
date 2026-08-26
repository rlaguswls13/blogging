from datetime import datetime
import hashlib
import os
import re
import unicodedata
from src.core.paths import run_directory, article_template_path
from src.core.files import write_json
from src.core.types import RunState, WorkflowStatus

def make_run_id(now: datetime) -> str:
    return re.sub(r"\D", "", now.isoformat()).split(".")[0][:14]

def slugify(value: str) -> str:
    # ArticleFrontmatter.validate_slug only accepts ASCII [a-z0-9-], so Korean
    # (and other non-ASCII) characters must be dropped, not just left as-is.
    # NFKD does not decompose Hangul into ASCII, so drop non-ASCII explicitly
    # after normalizing (keeps any embedded English/numbers from mixed topics).
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^\w\s-]", "", ascii_only).strip().lower()
    slug = re.sub(r"[\s_]+", "-", cleaned)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if slug:
        return slug
    # No ASCII survived (e.g. fully Korean topic) - fall back to a stable
    # hash of the original topic so the slug is still deterministic per-topic.
    digest = hashlib.md5(value.encode("utf-8")).hexdigest()[:8]
    return f"article-{digest}"

def create_run(topic: str) -> str:
    now = datetime.utcnow()
    run_id = make_run_id(now)
    dir_path = run_directory(run_id)
    
    # Ensure dir exists
    os.makedirs(dir_path, exist_ok=True)
    
    article_id = f"article-{run_id}"
    iso = now.isoformat() + "Z"
    
    state = RunState(
        runId=run_id,
        articleId=article_id,
        topic=topic,
        status=WorkflowStatus.CREATED,
        humanApproved=False,
        notionPageId=None,
        createdAt=iso,
        updatedAt=iso
    )
    
    write_json(dir_path / "state.json", state)
    
    with open(dir_path / "request.md", "w", encoding="utf-8") as f:
        f.write(f"# 블로그 작성 요청\n\n## 요청 주제\n\n{topic}\n\n## 생성 시각\n\n{iso}\n")
        
    with open(article_template_path, "r", encoding="utf-8") as f:
        template = f.read()
        
    rendered = (template
                .replace("{{articleId}}", article_id)
                .replace("{{title}}", topic)
                .replace("{{slug}}", slugify(topic))
                .replace("{{createdAt}}", iso))
                
    with open(dir_path / "article-template.md", "w", encoding="utf-8") as f:
        f.write(rendered)
        
    return run_id
