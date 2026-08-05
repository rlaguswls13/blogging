import os
import re
from pathlib import Path

# Resolve project root from environment variable or current working directory
blogging_root = os.environ.get("BLOGGING_ROOT")
project_root = Path(blogging_root).resolve() if blogging_root else Path.cwd()

runs_root = project_root / "temp" / "runs"
generated_root = project_root / "content" / "generated"
gate_path = project_root / "config" / "publish-gate.json"
article_template_path = project_root / "templates" / "article.md"
knowledge_graph_path = project_root / "content" / "knowledge-graph.json"

def run_directory(run_id: str) -> Path:
    if not re.match(r"^[a-zA-Z0-9_-]+$", run_id):
        raise ValueError("run-id에는 영문, 숫자, 밑줄, 하이픈만 사용할 수 있습니다.")
    return runs_root / run_id
