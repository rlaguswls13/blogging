from datetime import datetime
import os
import re
import unicodedata
from src.paths import run_directory, article_template_path
from src.files import write_json
from src.types import RunState, WorkflowStatus

def make_run_id(now: datetime) -> str:
    return re.sub(r"\D", "", now.isoformat()).split(".")[0][:14]

def slugify(value: str) -> str:
    # Handle Korean and other Unicode chars. Replace non-word (except Korean/English/numbers) chars.
    # To mimic normalized lowercase slugging:
    normalized = unicodedata.normalize("NFKD", value)
    # Remove chars that are not unicode alphanumeric, spaces, or hyphens
    cleaned = re.sub(r"[^\w\s-]", "", normalized, flags=re.UNICODE).strip().lower()
    slug = re.sub(r"[\s_]+", "-", cleaned)
    slug = re.sub(r"-+", "-", slug)
    return slug if slug else f"article-{int(datetime.utcnow().timestamp())}"

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
