import os
import re
from pathlib import Path
from typing import List, Optional

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


# 2026-08-23: content/posts/를 Basics/Advanced/ETC 하위폴더로 카테고리화(Obsidian 볼트
# 겸용) — wiki/Blog_Writing_Rules.md 7번 수칙의 세 라벨과 완전히 동일한 기준을 재사용한다.
# src/tools/apply_nav_labels.py(라이브 Blogger 라벨용)의 분류 로직과 반드시 일치시킬 것.
POST_CATEGORIES = ["Basics", "Advanced", "ETC"]
_ETC_KEYWORDS = {
    "ai agent", "graphrag", "ai framework", "llm", "llm agent",
    "kubernetes", "cloud-native", "devops", "http3", "quic", "autogen",
}
_BASICS_KEYWORDS = {"basics", "기초"}


def category_for_tags(tags: List[str]) -> str:
    """tags 목록에서 이 글이 속할 카테고리 폴더(Basics/Advanced/ETC)를 결정한다.
    우선순위: 명시적 'Basics'/'Advanced'/'ETC' 태그 > 키워드 휴리스틱(과거 글 백필용) > 기본값 Advanced."""
    lower = {t.lower() for t in tags if isinstance(t, str)}
    for cat in POST_CATEGORIES:
        if cat.lower() in lower:
            return cat
    if lower & _BASICS_KEYWORDS:
        return "Basics"
    if lower & _ETC_KEYWORDS:
        return "ETC"
    return "Advanced"


def post_path_for(slug: str, tags: List[str]) -> Path:
    """새로 저장할 글의 경로: content/posts/<Category>/<slug>.md"""
    category = category_for_tags(tags)
    return posts_root / category / f"{slug}.md"


def find_post_by_slug(slug: str) -> Optional[Path]:
    """이미 저장된 글을 카테고리 폴더 어디에 있든 slug로 찾는다(카테고리 이동 대비)."""
    for category in POST_CATEGORIES:
        candidate = posts_root / category / f"{slug}.md"
        if candidate.exists():
            return candidate
    # 구버전 평면 구조(마이그레이션 과도기) 대비 폴백
    legacy = posts_root / f"{slug}.md"
    return legacy if legacy.exists() else None


def all_post_paths() -> List[Path]:
    """카테고리 하위폴더를 포함해 발행된 글 전체를 재귀적으로 나열한다.
    파일명이 '_'로 시작하는 파일(예: _MOC.md 같은 Obsidian 유틸리티 노트)은 실제 글이 아니므로 제외한다
    (2026-08-23 MOC 도입 후 발견된 자기참조 버그 방지 — MOC 재생성 스크립트가 이전 실행의 _MOC.md를
    글로 오인해 목차에 스스로를 포함시키던 문제)."""
    return sorted(p for p in posts_root.glob("*/*.md") if not p.name.startswith("_"))
