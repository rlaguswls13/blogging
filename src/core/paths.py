import os
import re
from pathlib import Path

# Resolve project root from environment variable or current working directory
blogging_root = os.environ.get("BLOGGING_ROOT")
project_root = Path(blogging_root).resolve() if blogging_root else Path.cwd()

runs_root = project_root / "temp" / "runs"
posts_root = project_root / "content" / "posts"
gate_path = project_root / "src" / "core" / "publish_gate.json"
article_template_path = project_root / "wiki" / "templates" / "article.md"
theme_xml_path = project_root / "content" / "theme" / "blogger_site_theme.xml"
theme_css_path = project_root / "content" / "theme" / "blogger_post_style.css"

def run_directory(run_id: str) -> Path:
    if not re.match(r"^[a-zA-Z0-9_-]+$", run_id):
        raise ValueError("run-id에는 영문, 숫자, 밑줄, 하이픈만 사용할 수 있습니다.")
    return runs_root / run_id
